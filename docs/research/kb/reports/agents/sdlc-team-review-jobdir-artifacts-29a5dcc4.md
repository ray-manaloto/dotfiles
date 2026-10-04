
Source review used main at `36ab6bba`; the handoff worktree advanced independently to `0cc8d3c` during review.

| Severity | Claim | File:line | Evidence |
|---|---|---|---|
| High | Launch inventories live processes, without inventorying authored artifacts. | [coordinator_handoff.py:585](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/coordinator_handoff.py:585), [760](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/coordinator_handoff.py:760) | Census records PID, command, and log paths. Gathering reads process state and handoff text; it does not enumerate or migrate specs, rulings, or evidence files. |
| High | Retirement can succeed while authoritative artifacts remain ephemeral. | [coordinator_handoff.py:1119](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/coordinator_handoff.py:1119), [1162](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/coordinator_handoff.py:1162) | Checks cover live runs and `inFlight.tasks`, followed by `claude stop`. No committed-copy check or preservation certificate precedes stopping. Later removal remains separate. |
| High | Process adoption does not establish preservation of its eventual result. | [coordinator_handoff.py:1123](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/coordinator_handoff.py:1123), [test_coordinator_handoff.py:640](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_coordinator_handoff.py:640) | An adopted PID is discharged from process blockers without requiring a final rc record or durable result destination. Existing tests also permit retirement after the process disappears. |
| High | Inventorying only non-log files would miss the motivating evidence. | [session-2026-10-04d.md:96](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04d/docs/handoffs/session-2026-10-04d.md:96), [126](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04d/docs/handoffs/session-2026-10-04d.md:126) | The handoff identifies `land-1659.log` as the rc carrier and explicitly requires reading and copying it before removal. |
| High | A `tmp/`-only inventory misses additional load-bearing artifacts. | [dag_tick.py:246](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_tick.py:246), [codex_lane.py:429](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/codex_lane.py:429), [dag_project.py:99](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/dag_project.py:99) | Job-local `codex-lane/` contains verdicts, ownership/rework state, and exit evidence; `dag-binding.json` also resides in the job directory. |
| Medium | Durable placement is already policy, but enforcement checks instructions rather than preservation. | [agent-artifact-conventions.md:56](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/agent-artifact-conventions.md:56), [75](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/agent-artifact-conventions.md:75), [agent-report-persistence.md:56](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/agent-report-persistence.md:56) | Existing rules require promotion of later-session evidence and tracked specs/reports. Hook reminders do not verify Git blobs or artifact bytes. |
| Medium | Existing citation checks do not prove cleanup survival. | [doc_refs.py:182](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doc_refs.py:182), [296](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/doc_refs.py:296), [handoff_check.py:204](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py:204) | Machine-local and `.agent/` references are allowlisted; handoff checks verify filesystem presence and line ranges, without verifying commitment. |
| Medium | Existing tool interception cannot provide a hard cleanup guarantee. | [pretooluse-guard.sh:9](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/scripts/pretooluse-guard.sh:9), [39](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/scripts/pretooluse-guard.sh:39), [hook_guard.py:422](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py:422) | The wrapper intentionally fails open on interpreter/guard failure. Its removal guard covers plugin removal, without covering session `claude rm`. |
| Low | The rescue is committed locally, while consumer pointers remain partly disposable. | [session-2026-10-04d.md:79](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04d/docs/handoffs/session-2026-10-04d.md:79), [81](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-2026-10-04d/docs/handoffs/session-2026-10-04d.md:81) | Tracked copies are announced, but an active specification still points into `.agent/sdlc-specs/`. |

The five named specifications have matching SHA-256 bytes across the original job directory, `.agent/sdlc-specs/`, and the committed archive. Preservation commit `f8d984d881aa9427c21082ac0b506c5ad1633eda` was observed only on local branch `docs/handoff-2026-10-04d`; main contained no tracked files at that archive path. **Local preservation is verified; publication and delivery to main are not established.**

One premise needs narrowing: the flow **does read job-directory `state.json`** for identity and task counters. The defect is the absence of authored-artifact inventory and preservation checks.

Native Claude documentation confirms that session deletion removes scratch while retaining the resumable transcript. Transcript retention does not guarantee recovery of arbitrary files or redirected logs. Installed Claude `2.1.289` contains the same scratch-lifetime instruction. [Primary agent-view documentation](https://code.claude.com/docs/en/agent-view). Offline anchors: [$CC/agent-view.md:765](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:765), [530](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/agent-view.md:530).

**Ranked proposals**

1. **Check preservation at cleanup, with retirement preflight.**

   Mechanism: extend the public coordinator lifecycle interface with cleanup-time validation. Re-enumerate authored artifacts and evidence; record source digest, committed destination, revision, disposition, and successor adoption. Retirement provides early visibility; deletion performs the final check.

   Files: `coordinator_handoff.py`, `session_common.py`, corresponding tests, coordinator/session-handoff skills, and persistence rules.

   Fail closed: refuse cleanup for unresolved classification, unreadable files, mismatched bytes, absent committed copies, or evidence still being written. Require an artifact-specific discard override with a recorded reason, separate from `--accept-inflight`. Explicitly classify native operational files rather than requiring every job file to enter Git.

   Test/control: through the public interface in isolated Git/jobs fixtures, scratch-only specs and rc logs must refuse cleanup with nonzero rc before removal is invoked; exact committed copies must permit it. Staged-only copies, changed logs after inventory, unavailable Git, and out-of-scope overrides must refuse. Reverting enforcement must make those refusal assertions fail.

   Cost: medium to high. This catches the deletion path directly. A repository wrapper protects routed cleanup; direct native CLI or agent-view deletion remains a bypass until mediation is qualified.

2. **Enforce durable authority at ratification and dispatch.**

   Mechanism: permit scratch drafts, but require the ratified authority to identify an immutable committed artifact before implementation dispatch. Use the existing `docs/specs/` destination for new specs; retain rescued raw files as archival evidence. Update active consumer pointers.

   Files: `.claude/agents/spec-scribe.md`, artifact/persistence rules, the SDLC dispatch skill and its public validation interface/tests.

   Fail closed: reject ratified dispatch backed solely by job scratch, ignored `.agent/`, or matching uncommitted working-tree bytes.

   Test/control: isolated public dispatch accepts a committed authoritative spec and rejects identical scratch-only or staged-only copies. Preserve a legitimate draft arm. Reverting validation must make the rejection assertion fail.

   Cost: medium. This prevents new stranded specs; logs and unregistered evidence still need cleanup coverage.

3. **Add a complete preservation inventory to the successor brief.**

   Mechanism: inventory the whole relevant job directory, including evidence logs and `codex-lane/`. List source, digest, kind, consumer, intended destination, and outstanding disposition. Reconcile coordinator-authored artifacts with delegate briefs and reports.

   Files: `coordinator_handoff.py`, its tests, coordinator/session-handoff skills, and report-persistence rules.

   Fail closed: unknown or unreadable artifacts remain explicit obligations. An unavailable inventory cannot mean “nothing owed.” Successor startup may proceed with unresolved obligations; cleanup must refuse them.

   Test/control: public launch against an isolated fixture containing a spec, ruling, completed rc log, and lane verdict must expose all four obligations. Reverting inventory generation must fail those assertions. Add an artifact after launch to verify cleanup rescans.

   Cost: medium. Inventory improves discovery but cannot prevent deletion alone.

4. **Add scoped native protection where applicable.**

   Mechanism: pair native `WorktreeCreate`/`WorktreeRemove` for qualifying hook-created worktrees; run the preservation check before allowing removal.

   Files: `.claude/settings.json`, a Python handler, and corresponding tests.

   Fail closed: the handler returns nonzero while leaving the worktree directory intact. Native documentation states this can retain the session during qualifying background-session deletion. It does not establish coverage for main-checkout jobs. `SessionEnd` cannot veto termination. [Primary hook documentation](https://code.claude.com/docs/en/hooks); offline anchors: [$CC/hooks.md:2996](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:2996), [3041](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:3041), [3344](/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md:3344).

   Test/control: isolated qualifying-worktree refusal must retain session/directory; allowance must remove them. Separately test main-checkout cleanup reachability. A worktree-only success cannot establish universal coverage.

   Cost: medium, with narrower scope. Universal native archival or deletion-veto availability remains unproven; no destructive native probe ran.

**Recommended option:** combine proposals 1–3. Enforce durable authority when a draft becomes ratified, make migrations discoverable during handoff, and verify preservation again before deletion. Another documentation convention or a retirement-only snapshot would leave the motivating loss path open.

The successor should adopt live work and settled results separately. Preserve command identity, actual rc—including failures—final log bytes, lane verdicts, relevant bindings, and durable consumer pointers. PID disappearance is not rc 0; copying an actively appended log does not settle its final evidence. Existing `.agent/gate-results` records can supply inputs but require promotion when later sessions rely on them.

“Tracked” also needs a precise threshold: indexed, committed, successor-accessible, and published are distinct states. A committed blob can protect same-host deletion; another clone requires a reachable published carrier.

**Research execution and limits**

Applied skills: `codex-sdlc-team` and `research-sweep`. No connector apps ran. The required native `fnox exec` process ran the pinned `research-fanout` task, using Exa API, Context7 `ctx7`, Firecrawl developer/search routes, the installed Last30Days plugin script, and GitHub `gh` routes. Additional `gh` code searches, Claude version/help reads, and primary web-document reads ran.

| Route | Manifest result |
|---|---|
| GitHub issues/PRs | `empty_verified` |
| GitHub Discussions | `empty_unverified`: `canary returned 0 items` |
| GitHub releases | `empty_verified` |
| Exa | `ok`, 10 items |
| Context7 | `ok`, 5 items |
| Firecrawl developer | `ok`, 10 items |
| Firecrawl search | `error`: `exited 1: Error: Request failed with status code 402 \|` |
| Last30Days | `ok`, 10 items |

**RESEARCH INCOMPLETE:** strict-five exited **1** because Discussions did not complete and Firecrawl search failed. GitHub metadata additionally reported `has_discussions=false`; the strict receipt still failed. Manifest identity matched this turn, and all **8/8** raw-file hashes matched. [Research manifest](/Users/rmanaloto/.codex/research-coverage/01a106ef-a417-7552-8e38-ed681ad94203/01a106ef-ac09-7821-b7cb-ab73584468eb/manifest.json).

Specialist gates were **NOT RUN**, as requested: Python’s pytest gate and documentation’s lint-docs gate have no exit codes. The harness specialist performed read-only review.

## GitHub repos touched

- `ray-manaloto/dotfiles` — local source, rules, tests, and preservation history.
- `ray-manaloto/knowledge-base` — local offline primary-document corpus.
- `anthropics/claude-code` — remote research and primary-source discovery.

No GitHub mutations occurred. No other specialists were spawned.

Specialists spawned:
