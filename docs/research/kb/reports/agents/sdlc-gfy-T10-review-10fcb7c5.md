**Overall status: HOLD.** The static T10 port checks pass. Existing test failures remain unresolved, and the source-freeze risk to T2 is confirmed. Both specialists completed their reviews; neither ran gates or wrote files.

**A — Cold review of `3d7c02c78800a131056bd4338ff675c12c6de347`**

No missing dependency or port-specific defect was identified.

| Port check | Result |
|---|---|
| Parent commit | Exactly upstream v0.9.76, `0010e25d0d983bc127cef0ee0f7e490bed74e44c` |
| Upstream-to-port diff | Exactly four added files; 9,744 insertions, zero deletions |
| Comparison with original `726e6a63ca90cc2a9e2b697c531730308cad5dae` | Five requested paths identical; `git diff --exit-code` **rc=0** |
| `tools/__init__.py` | Identical empty-file blob in upstream, original and port |
| Excluded-commit dependencies | None identified; engine imports are standard library only |
| Task and HTTP workers | Both select the repository-local engine |

Findings:

- **P1 — Runtime readiness remains unproven.** The engine retains its initial process-group observation and refuses when that observation is not `True`, even if subsequent cleanup succeeds. Existing [failure evidence](/Users/rmanaloto/dev/github/ray-manaloto/graphify.evidence/0976/T10-pytest-rerun-failed.out:26) records `group_observation: null` alongside `process_group_settled: true`. In [the observation function](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:669), `null` specifically follows `PermissionError`. The [refusal logic](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:516) therefore cannot be explained solely by exceeding the cleanup grace period. Host load is an unproven cause. This behavior was inherited unchanged; it is a validation blocker, not evidence of an incomplete port.

- **P2 — The report’s ambient mise Git-shim hypothesis does not fit the inspected callers.** The [report](/Users/rmanaloto/dev/github/ray-manaloto/graphify.evidence/0976/T10-report.md:29) suggests an ambient `PATH` shim. Both [the engine](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:298) and [test fixtures](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tests/test_fork_maintenance.py:31) resolve Git through a fixed system-first path. Another executed path or different bytes would require evidence.

Test inspection found meaningful public-interface coverage using temporary Git repositories: source preservation, ancestry, replay idempotence, hook nonexecution, an actual autostash control, and failed-publication recovery. The process-group survivor test exercises a real descendant, but that lower-level test does not establish public CLI success. Both Python files parsed successfully through AST analysis; neither was imported or executed.

The Python specialist also observed an inherited [`# noqa: BLE001`](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:3054). This fails its no-inline-suppression checklist, but it did not establish a Graphify-specific prohibition or a newly introduced port defect.

**B — Source-freeze risk to T2**

The frozen evidence checks passed:

| Evidence | Verified value |
|---|---|
| Plan SHA-256 | `e3002af4649f8244b941cb6a6ff2b1be2fc00b28a9e0fd5c6c0206f7ce8dc3e7` |
| Historical status bytes | `b' M uv.lock\n?? .codex/config.toml\n'` — 33 bytes |
| Status SHA-256 | `a48028a8ed597484e5e6985343f585f9fcb3ca2651bde6cc3030f56b77c50727` |
| Command-records SHA-256 | `be81180f26bd4a531afe3420eeb230402242f8687a96c9254b2488869428342d` |
| Historical preview | Recorded **rc=0**, `planned`, empty stderr |
| Reviewed runner HEAD and files | Exact T10 commit; engine, skill and mise file match |

These are historical records. **The live main checkout’s identity was not inspected.**

Findings:

- **P2 — Installing T10 into the frozen source would invalidate the approval.** The plan pins source HEAD `3c9b930f386f80c393fe658e1afb685030828c6a`, branch `kb-pin/openai-cli-backend-v0.9.57`, origin, Git directories, worktree and status digest. Checking out or committing T10 changes identity; copying its new files can change status. [Source comparison](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:2344) refuses drift.

- **P2 — The status digest does not freeze dirty-file contents between preview and apply.** Further edits to already-modified `uv.lock`, or to existing untracked `.codex/config.toml`, can leave the complete porcelain output unchanged. [Status hashing](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:794) contains no content hash. The fuller [source snapshot](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:2255) is taken [during apply](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:2856), protecting changes during that attempt, rather than binding dirty contents to preview.

- **P3 — Two premises need narrower wording.** Premise 4’s `?? .codex/` is directory shorthand; [the bound record](/Users/rmanaloto/dev/github/ray-manaloto/graphify.evidence/0976/plan.json:835) says `?? .codex/config.toml`. The specialist stopped using the shorthand as exact digest input. Premise 5’s universal “path + XY only” claim omits rename/copy paths and quoting documented in [installed Git documentation](/Library/Developer/CommandLineTools/usr/share/man/man1/git-status.1:274). That universal premise was rejected; content blindness remains supported for the actual two ordinary lines.

Staging, restoring, stashing, committing, deleting or adding visible paths, changing ignore behavior, or changing repository identity can invalidate the status or identity pin. Content-only edits and ignored-file changes may evade it.

**Safest T2 procedure**

1. Keep source contents, index, HEAD, branch and origin frozen while the runtime blocker is resolved. The [existing report](/Users/rmanaloto/dev/github/ray-manaloto/graphify.evidence/0976/T10-report.md:67) already leaves pytest open and prohibits apply pending its prerequisite.
2. Once readiness is established, run the reviewed task from the separate T10 worktree with the frozen main checkout explicitly supplied as `--source-repo`. The [skill permits a separate source](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/.claude/skills/graphify-fork-maintenance/SKILL.md:8); [preview evidence](/Users/rmanaloto/dev/github/ray-manaloto/graphify.evidence/0976/plan.json:843) already names that worktree’s interpreter. Plan validation does not bind the runner commit or engine hash, so preserve the reviewed runner bytes too.
3. Preserve the plan and existing approval pin. Use an ordinary explicit committer, a unique attempt branch, and separate output/evidence destinations outside main and its Git directories. The tool’s [overlap checks](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/tools/fork_maintenance.py:2381) refuse destinations beneath the source.
4. On refusal, conflict, timeout or uncertainty, stop and retain evidence. Do not rewrite the plan, weaken checks, remove ownership or retry destructively. [Skill stop rules](/Users/rmanaloto/dev/github/ray-manaloto/graphify/.claude/worktrees/gfy-t10/.claude/skills/graphify-fork-maintenance/SKILL.md:95).
5. If source work must resume, treat the old approval as stale. After authorized settlement, use a fresh preview and inspect its new pin.

**Verification accounting**

| Specialist | Normal gate | This review |
|---|---|---|
| Python | pytest | **NOT RUN — prohibited** |
| Config | `mise run lint` | **NOT RUN — prohibited** |

Existing evidence records the original pytest run as **rc=1, 37 failed / 296 passed**, and the failed-test rerun as **rc=1, 12 failed / 25 passed**. Neither result was reproduced or reclassified as environmental.

The Python specialist reported all read/analysis commands **rc=0**. The config specialist reported all 11 read commands **rc=0**. Truncated initial displays were followed by targeted reads. The dispatcher’s initial lookup of nonexistent `.claude/agents/` files returned **rc=1**; the actual `.codex/agents/` roster read returned **rc=0**.

No gates, preview, apply, network calls, writes, Git mutations or direct main-checkout inspection occurred. No others were spawned.

Specialists spawned:

- `sdlc-python-specialist` — `/root/t10_cold_review`
- `sdlc-config-specialist` — `/root/t2_freeze_risk`

